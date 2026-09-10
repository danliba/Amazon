% compute particle trajectories in three-dimensional flow fields

% setup parameters
%  number of particles to release
pnum=1000;
% longitude and latitude ranges to release particles
releasebox=[-100 -75 -48 -40];
% temperature range to release particles
temprange=[13 22];
% depth range  to release particles
deprange=[-30 -15];
% output frequency: every how many time step
outrate=4;

%  start end end year of computation
styear=2015;
enyear=2017;
%  start and end month of computation
startmon=1;
endmon=6;
%  start and end day of computation
startday=1;
endday=20;

% time step [sec]
dt=3600.0;

% netcdf file
% Input file path
pathin='/Volumes/G-RAID2019/CMEMS/OffPeru';
% output file path
pathout='/Volumes/G-RAID2019/CMEMS/OffPeru';
% Output file name
outfn=sprintf('OffPeruJackMac_%04d%02d_%04d%02d.nc',...
    styear,startmon,enyear,endmon);
outfn=fullfile(pathout,outfn);

% computing starting and ending date in Julian date
startdate=datenum(styear,startmon,startday,0,0,0);
enddate=datenum(enyear,endmon,endday,0,0,0);
% generating all the time in Julian date for the computation
times=startdate:dt/86400:enddate;
% returns year, month, days,hours, minites,seconds
[yrs,mos,das,hrs,mis,ses]=datevec(times);
% count the number of iteration to compute
numiter=length(times);

% generate the figure window
figure
% initialize the output index
iout=0;
% start the main loop
for i=1:1:numiter
    % obtain current time
    timenow=times(i);
    % display current time
    disp(datestr(timenow));
    % get current year
    yr=yrs(i);
    % define the input file
    ncfn=sprintf('OffPeru%04d.nc',yr);
    ncfnfull=fullfile(pathin,ncfn);
    if i==1
        % get ready for the grid
        depth3d=ncread(ncfnfull,'depth');
        dz=ncread(ncfnfull,'dz');
        dx=ncread(ncfnfull,'dx');
        dy=ncread(ncfnfull,'dy');
        loni=ncread(ncfnfull,'longitude');
        lati=ncread(ncfnfull,'latitude');
        
        % prepare 3-d distance [m] and layer thickness [m]
        dx3d=repmat(dx,[1 1 size(depth3d,3)]);
        dy3d=repmat(dy,[1 1 size(depth3d,3)]);
        lon3d=repmat(loni,[1 1 size(depth3d,3)]);
        lat3d=repmat(lati,[1 1 size(depth3d,3)]);
        
        dz3d=repmat(shiftdim(dz(:),-2),[size(dx3d,1) size(dx3d,2) 1]);
        
        % grid for the computation is monotinic indice
        % Y X Z matlab dimension order
        [xi,yi,zi]=meshgrid(1:1:size(dx3d,1),1:1:size(dx3d,2),1:1:size(dx3d,3));
        
        % reorder the matrix to matlab order
        % Y X Z matlab dimension order
        
        lon3d=permute(lon3d,[2 1 3]);
        lat3d=permute(lat3d,[2 1 3]);
        depth3d=permute(depth3d,[2 1 3]);
        dx3d=permute(dx3d,[2 1 3]);
        dy3d=permute(dy3d,[2 1 3]);
        dz3d=permute(dz3d,[2 1 3]);
        
    end
    
    
    % rading time vector of the input
    timein=ncread(ncfnfull,'time');
    
    id0=find(timein==timenow);
    if ~isempty(id0)
        % there is an output at exactly the same time
        uinow=ncread(ncfnfull,'u',[1 1 1 id0],[Inf Inf Inf 1],[1 1 1 1]);
        vinow=ncread(ncfnfull,'v',[1 1 1 id0],[Inf Inf Inf 1],[1 1 1 1]);
        winow=ncread(ncfnfull,'w',[1 1 1 id0],[Inf Inf Inf 1],[1 1 1 1]);
        tempinow=ncread(ncfnfull,'temp',[1 1 1 id0],[Inf Inf Inf 1],[1 1 1 1]);
        saltinow=ncread(ncfnfull,'salt',[1 1 1 id0],[Inf Inf Inf 1],[1 1 1 1]);
        id1p=999;
        id2p=999;
        
    else
        id1=max(find(timein<timenow));
        id2=min(find(timein>timenow));
        time1=timein(id1);
        time2=timein(id2);
        dT=time2-time1;
        delT=timenow-time1;
        
        if id1==id1p & id2==id2p
            % velocity filed at 2 time stamps are unchanged
        else
            disp('new data are read')
            ui1=ncread(ncfnfull,'u',[1 1 1 id1],[Inf Inf Inf 1],[1 1 1 1]);
            vi1=ncread(ncfnfull,'v',[1 1 1 id1],[Inf Inf Inf 1],[1 1 1 1]);
            wi1=ncread(ncfnfull,'w',[1 1 1 id1],[Inf Inf Inf 1],[1 1 1 1]);
            tempi1=ncread(ncfnfull,'temp',[1 1 1 id1],[Inf Inf Inf 1],[1 1 1 1]);
            salti1=ncread(ncfnfull,'salt',[1 1 1 id1],[Inf Inf Inf 1],[1 1 1 1]);
            ui2=ncread(ncfnfull,'u',[1 1 1 id2],[Inf Inf Inf 1],[1 1 1 1]);
            vi2=ncread(ncfnfull,'v',[1 1 1 id2],[Inf Inf Inf 1],[1 1 1 1]);
            wi2=ncread(ncfnfull,'w',[1 1 1 id2],[Inf Inf Inf 1],[1 1 1 1]);
            tempi2=ncread(ncfnfull,'temp',[1 1 1 id2],[Inf Inf Inf 1],[1 1 1 1]);
            salti2=ncread(ncfnfull,'salt',[1 1 1 id2],[Inf Inf Inf 1],[1 1 1 1]);
            dui=ui2-ui1;
            dvi=vi2-vi1;
            dwi=wi2-wi1;
            dtempi=tempi2-tempi1;
            dsalti=salti2-salti1;
        end
        % do temporal interpolation
        uinow=delT.*dui./dT + ui1;
        vinow=delT.*dvi./dT + vi1;
        winow=delT.*dwi./dT + wi1;
        saltinow=delT.*dsalti./dT + salti1;
        tempinow=delT.*dtempi./dT + tempi1;
        
        clear ui2 vi2 wi2 salti2 tempi2
        
        if isempty(id2)
            % in this case, the timenow is outside
            % But this notgonna happen if the daily output is at midnight
            disp('it happens men')
        end
        id1p=id1;
        id2p=id2;
        
    end
    
    
    uinow=permute(uinow,[2 1 3]);
    vinow=permute(vinow,[2 1 3]);
    winow=permute(winow,[2 1 3]);
    saltinow=permute(saltinow,[2 1 3]);
    tempinow=permute(tempinow,[2 1 3]);
    winow=0.5.*(winow(:,:,1:end-1)+winow(:,:,2:end));
    
    if i==1
        
        % initialize the particles
        % obtain 3D indice which satisfy the ranges
        releaseindx=find(temprange(1)<=tempinow & tempinow<=temprange(2) & ...
            releasebox(1)<=lon3d & lon3d<=releasebox(2) & ...
            releasebox(3)<=lat3d & lat3d<=releasebox(4) & ...
            deprange(1)<=depth3d & depth3d<=deprange(2));
        numindx=length(releaseindx);
        rn=round(rand(pnum,1).*numindx);
        rnx=(rand(pnum,1)-0.5).*0.5;
        rny=(rand(pnum,1)-0.5).*0.5;
        rnz=(rand(pnum,1)-0.5).*0.5;
        Jackx=xi(releaseindx(rn))+rnx;
        Jacky=yi(releaseindx(rn))+rny;
        Jackz=zi(releaseindx(rn))+rnz;
        
        % generate outputfile
        ncout=netcdf.create(outfn,'CLOBBER');
        dimJ=netcdf.defDim(ncout,'pnum',pnum);
        dimT=netcdf.defDim(ncout,'time',netcdf.getConstant('NC_UNLIMITED'));
        
        varid1=netcdf.defVar(ncout,'times','double',dimT);
        varid2=netcdf.defVar(ncout,'lon','double',[dimJ dimT]);
        varid3=netcdf.defVar(ncout,'lat','double',[dimJ dimT]);
        varid4=netcdf.defVar(ncout,'depth','double',[dimJ dimT]);
        varid5=netcdf.defVar(ncout,'temp','double',[dimJ dimT]);
        varid6=netcdf.defVar(ncout,'salt','double',[dimJ dimT]);
        varid7=netcdf.defVar(ncout,'u','double',[dimJ dimT]);
        varid8=netcdf.defVar(ncout,'v','double',[dimJ dimT]);
        varid9=netcdf.defVar(ncout,'w','double',[dimJ dimT]);
        varid10=netcdf.defVar(ncout,'xi','double',[dimJ dimT]);
        varid11=netcdf.defVar(ncout,'yi','double',[dimJ dimT]);
        varid12=netcdf.defVar(ncout,'zi','double',[dimJ dimT]);
        
        netcdf.endDef(ncout);
        netcdf.close(ncout)
        
        
        
        
    end
    
    % spatial interpolation
    Jacku=interp3(xi,yi,zi,uinow,Jackx,Jacky,Jackz);
    Jackv=interp3(xi,yi,zi,vinow,Jackx,Jacky,Jackz);
    Jackw=interp3(xi,yi,zi,winow,Jackx,Jacky,Jackz);
    
    Jackdx=interp3(xi,yi,zi,dx3d,Jackx,Jacky,Jackz);
    Jackdy=interp3(xi,yi,zi,dy3d,Jackx,Jacky,Jackz);
    Jackdz=interp3(xi,yi,zi,dz3d,Jackx,Jacky,Jackz);
    
    % obtain first guess positions
    Jackxguess=Jackx+Jacku./Jackdx.*dt;
    Jackyguess=Jacky+Jackv./Jackdy.*dt;
    Jackzguess=Jackz+Jackw./Jackdz.*dt;
    
    % get guess new u, v, w
    Jackuguess=interp3(xi,yi,zi,uinow,Jackxguess,Jackyguess,Jackzguess);
    Jackvguess=interp3(xi,yi,zi,vinow,Jackxguess,Jackyguess,Jackzguess);
    Jackwguess=interp3(xi,yi,zi,winow,Jackxguess,Jackyguess,Jackzguess);
    
    Jackdxguess=interp3(xi,yi,zi,dx3d,Jackxguess,Jackyguess,Jackzguess);
    Jackdyguess=interp3(xi,yi,zi,dy3d,Jackxguess,Jackyguess,Jackzguess);
    Jackdzguess=interp3(xi,yi,zi,dz3d,Jackxguess,Jackyguess,Jackzguess);
    
    % obtain the new position positions
    Jackx=Jackx+(Jacku+Jackuguess)./(Jackdx+Jackdxguess).*dt;
    Jacky=Jacky+(Jackv+Jackvguess)./(Jackdy+Jackdyguess).*dt;
    Jackz=Jackz+(Jackw+Jackwguess)./(Jackdz+Jackdzguess).*dt;
    
    % obtain temp and salt at the new positions
    Jacktemp=interp3(xi,yi,zi,tempinow,Jackx,Jacky,Jackz);
    Jacksalt=interp3(xi,yi,zi,saltinow,Jackx,Jacky,Jackz);
    % compute lon, lat and depth
    Jacklon=interp2(xi(:,:,1),yi(:,:,1),loni',Jackx,Jacky);
    Jacklat=interp2(xi(:,:,1),yi(:,:,1),lati',Jackx,Jacky);
    Jackdep=interp1(squeeze(zi(1,1,:)),squeeze(depth3d(1,1,:)),Jackz);
    
    if mod(i,outrate)==0
        iout=iout+1;
        disp('output is written')
        ncwrite(outfn,'times',timenow,[iout],[1]);
        ncwrite(outfn,'lon',Jacklon,[1 iout],[1 1]);
        ncwrite(outfn,'lat',Jacklat,[1 iout],[1 1]);
        ncwrite(outfn,'depth',Jackdep,[1 iout],[1 1]);
        ncwrite(outfn,'temp',Jacktemp,[1 iout],[1 1]);
        ncwrite(outfn,'salt',Jacksalt,[1 iout],[1 1]);
        ncwrite(outfn,'xi',Jackx,[1 iout],[1 1]);
        ncwrite(outfn,'yi',Jacky,[1 iout],[1 1]);
        ncwrite(outfn,'zi',Jackz,[1 iout],[1 1]);
        ncwrite(outfn,'u',Jacku,[1 iout],[1 1]);
        ncwrite(outfn,'v',Jackv,[1 iout],[1 1]);
        ncwrite(outfn,'w',Jackw,[1 iout],[1 1]);
        
        pcolor(loni',lati',tempinow(:,:,end))
        shading flat
        caxis([8 26])
        colormap jet
        colorbar
        hold on
        plot(Jacklon,Jacklat,'k.');
        xlabel('longitude')
        ylabel('latitude')
        title(datestr(timenow))
        pause(0.1)
        clf
    end
end


